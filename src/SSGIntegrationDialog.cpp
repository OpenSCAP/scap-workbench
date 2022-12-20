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

/*
 * Given the string list passed as the first argument,
 * either make sure that the passed value is the first item,
 * or don't do anything (if the value is not present in the string).
 *
 * Returns true if the priority item matched a list item, returns false otherwise.
 */
static bool put_value_as_first_item(QStringList& list, const QString& value)
{
    const int value_index = list.indexOf(value);
    if (value_index == -1)
    {
        return false;
    }
    list.removeAt(value_index);
    list.push_front(value);
    return true;
}

static void ensure_good_string_list_ordering(QStringList& list, const QStringList& priority_items, int& matched_priority_items)
{
    list.sort();
    for (QStringList::const_reverse_iterator it = priority_items.rbegin();
         it != priority_items.rend(); ++it)
    {
        if (put_value_as_first_item(list, * it))
        {
            matched_priority_items++;
        }
    }
}

void SSGIntegrationDialog::scrapeSSGVariants()
{
    const QDir& dir = getSSGDirectory();
    QStringList variants = dir.entryList(QDir::Files | QDir::NoDotAndDotDot);
    QComboBox* cBox = mUI.contentComboBox;

    const QString first_items = QString(SCAP_WORKBENCH_PREFERRED_DATASTREAM_BASENAMES);
    const QStringList priority_products = first_items.split(",");
    int matched_priority_items = 0;
    ensure_good_string_list_ordering(variants, priority_products, matched_priority_items);
    for (QStringList::const_iterator it = variants.constBegin();
         it != variants.constEnd(); ++it)
    {
        QString name = *it;

        if (!name.startsWith("ssg-") || !name.endsWith("-ds.xml") || name.length() < 12)
            continue; // TODO: Warn?

        name.remove(0, 4); // remove prefix "ssg-"
        name.chop(7); // remove suffix "-ds.xml"

        QString label = name;

        // Make the label nicer for known variants
        if (label.startsWith("rhel") || label.startsWith("ol"))
        {
            // use RHEL instead of rhel and OL instead of ol
            label = name.toUpper();
        }
        else if (label.startsWith("centos")) // use CentOS instead of centos
            label.replace(0, 6, "CentOS");

        else if (label.startsWith("jre")) // use JRE instead of jre
            label.replace(0, 3, "JRE");

        else if (label.startsWith("sl")) // use SL instead of sl
            label.replace(0, 2, "SL");

        else
            label[0] = label[0].toUpper(); // Capitalize first letter

        cBox->addItem(label, QVariant(name));

    }
    if (matched_priority_items)
    {
        cBox->insertSeparator(matched_priority_items);
    }
    cBox->insertSeparator(cBox->count());
    cBox->addItem(QString("Other SCAP Content"), QVariant(QString("other-scap-content")));

    cBox->setCurrentIndex(0);
}
