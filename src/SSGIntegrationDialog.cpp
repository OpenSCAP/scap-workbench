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
    mUI.setupUi(this);
    mUI.ssgLogo->setPixmap(getSharePixmap("ssg_logo.png"));

    scrapeSSGVariants();

    QObject::connect(
        mUI.dismissButton, SIGNAL(released()),
        this, SLOT(reject())
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

bool SSGIntegrationDialog::isSSGAvailable()
{
    return getSSGDirectory().exists();
}

void SSGIntegrationDialog::variantRequested()
{
    QObject* sender = QObject::sender();
    QPushButton* button = dynamic_cast<QPushButton*>(sender);

    if (!button)
        return;

    const QString variant = button->property("ssg_variant").toString();

    QDir dir(getSSGDirectory());
    dir.cd(variant);

    mSelectedSSGFile = dir.absoluteFilePath(QString("ssg-%1-ds.xml").arg(variant));
    accept();
}

void SSGIntegrationDialog::scrapeSSGVariants()
{
    const QDir& dir = getSSGDirectory();
    const QStringList variants = dir.entryList(QDir::Dirs | QDir::NoDotAndDotDot);

    for (QStringList::const_iterator it = variants.constBegin();
         it != variants.constEnd(); ++it)
    {
        QString name = *it;

        // Make the label nicer for known variants
        if (name.startsWith("rhel")) // use RHEL instead of rhel
            name = name.toUpper();
        else if (name.startsWith("fedora")) // use Fedora instead of fedora
            name[0] = 'F';

        QPushButton* button = new QPushButton(name, mUI.variants);
        button->setProperty("ssg_variant", QVariant(*it));
        mUI.variants->layout()->addWidget(button);

        QObject::connect(
            button, SIGNAL(released()),
            this, SLOT(variantRequested())
        );
    }
}
