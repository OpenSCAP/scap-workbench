/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "SSGIntegrationDialog.h"
#include "Utils.h"

#include <QDir>

SSGIntegrationDialog::SSGIntegrationDialog(QWidget* parent):
    QDialog(parent)
{
    loadOtherContent = false;
    mUI.setupUi(this);
    mUI.ssgLogo->setPixmap(getSharePixmap("ssg_logo.png"));

    scrapeSSGVariants();

    QObject::connect(
        mUI.dismissButton, SIGNAL(released()),
        this, SLOT(reject())
    );

    QObject::connect(
        mUI.loadButton, SIGNAL(released()),
        this, SLOT(loadContent())
    );
}

SSGIntegrationDialog::~SSGIntegrationDialog()
{}

void SSGIntegrationDialog::setDismissLabel(const QString& label)
{
    mUI.dismissButton->setText(label);
}

const QString& SSGIntegrationDialog::getSelectedSSGFile() const
{
    return mSelectedSSGFile;
}

bool SSGIntegrationDialog::loadOtherContentSelected()
{
    return loadOtherContent;
}

bool SSGIntegrationDialog::isSSGAvailable()
{
    return getSSGDirectory().exists();
}

void SSGIntegrationDialog::loadContent()
{
    QComboBox* cBox = mUI.contentComboBox;

    const QString variant = cBox->itemData(cBox->currentIndex()).toString();

    if (variant.isEmpty())
        return;

    if (!variant.compare("other-scap-content"))
    {
        loadOtherContent = true;
    }
    else
    {
        const QDir& dir(getSSGDirectory());

        mSelectedSSGFile = dir.absoluteFilePath(QString("ssg-%1-ds.xml").arg(variant));
    }
    accept();
}

void SSGIntegrationDialog::scrapeSSGVariants()
{
    const QDir& dir = getSSGDirectory();
    const QStringList variants = dir.entryList(QDir::Files | QDir::NoDotAndDotDot);
    QComboBox* cBox = mUI.contentComboBox;

    int lastFavoriteIndex = 0;
    for (QStringList::const_iterator it = variants.constBegin();
         it != variants.constEnd(); ++it)
    {
        QString name = *it;

        if (!name.startsWith("ssg-") || !name.endsWith("-ds.xml") || name.length() < 12)
            continue; // TODO: Warn?

        name.remove(0, 4); // remove prefix "ssg-"
        name.chop(7); // remove suffix "-ds.xml"

        QString label = name;

        bool favorite = false;
        // Make the label nicer for known variants
        if (label.startsWith("rhel"))
        {
            // use RHEL instead of rhel
            label = name.toUpper();
            favorite = true;
        }
        else if (label.startsWith("centos")) // use CentOS instead of centos
            label.replace(0, 6, "CentOS");

        else if (label.startsWith("jre")) // use JRE instead of jre
            label.replace(0, 3, "JRE");

        else if (label.startsWith("sl")) // use SL instead of sl
            label.replace(0, 2, "SL");

        else
            label[0] = label[0].toUpper(); // Capitalize first letter

        if (label.startsWith("Fedora"))
            favorite = true;

        if (favorite)
            cBox->insertItem(lastFavoriteIndex++, label, QVariant(name));

        else
            cBox->addItem(label, QVariant(name));

    }
    cBox->insertSeparator(cBox->count());
    cBox->addItem(QString("Other SCAP Content"), QVariant(QString("other-scap-content")));

    cBox->insertSeparator(lastFavoriteIndex);
    cBox->setCurrentIndex(0);
}
